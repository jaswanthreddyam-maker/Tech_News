export interface MetricValue<T> {
  value: T;
  source: string;
  updated_at: string;
  window: string;
}

export interface HistoricalCounts {
  discovered: number;
  queued: number;
  fetched: number;
  filtered: number;
  deduplicated: number;
  processed: number;
  published: number;
  failed: number;
}

export interface TelemetrySnapshotV3 {
  _meta?: {
    schema_version: number;
    sequence: number;
    snapshot_id: string;
    boot_id: string;
    generated_at: string;
    max_age_ms: number;
  };
  current_state: {
    queue_depth: MetricValue<number>;
    active_workers: MetricValue<number>;
    active_crawlers: MetricValue<number>;
    ai_queue: MetricValue<number>;
  };
  throughput: {
    ingestion_rate_sec: MetricValue<number>;
  };
  quality: {
    thumbnail_coverage: MetricValue<number>;
    average_resolution: MetricValue<number>;
    broken_images: MetricValue<number>;
    fallback_usage: MetricValue<number>;
    thumbnail_source_distribution: MetricValue<Record<string, number>>;
    average_ranking_score: MetricValue<number>;
  };
  historical: {
    all_time: HistoricalCounts;
    last_24h: HistoricalCounts;
  };
  ai_engine: {
    enabled: boolean;
    provider_name: string;
    provider_model: string;
    healthy: boolean;
    success_rate: MetricValue<number>;
    fallback_rate: MetricValue<number>;
    cost_usd_today: MetricValue<number>;
    tokens_total: MetricValue<number>;
    average_latency_p95: MetricValue<number>;
  };
  ranking_engine: {
    enabled: boolean;
    last_run: string | null;
    articles_evaluated: MetricValue<number>;
    active_articles: MetricValue<number>;
    expired_articles: MetricValue<number>;
  };
}

export type ConnectionState = "loading" | "connected" | "reconnecting" | "failed";

export interface TelemetryTransport {
  connect(): void;
  disconnect(): void;
}

export interface TelemetryTransportCallbacks {
  onSnapshot(snapshot: TelemetrySnapshotV3): void;
  onHeartbeat(heartbeat: any): void;
  onError(error: any): void;
  onOpen?(): void;
}

export class SSETransport implements TelemetryTransport {
  private url: string;
  private callbacks: TelemetryTransportCallbacks;
  private eventSource: EventSource | null = null;

  constructor(url: string, callbacks: TelemetryTransportCallbacks) {
    this.url = url;
    this.callbacks = callbacks;
  }

  connect(): void {
    if (this.eventSource) return;

    this.eventSource = new EventSource(this.url);

    this.eventSource.addEventListener("snapshot", (event) => {
      try {
        const parsed = JSON.parse(event.data);
        this.callbacks.onSnapshot(parsed);
      } catch (err) {

        this.callbacks.onError(err);
      }
    });

    this.eventSource.addEventListener("heartbeat", (event) => {
      try {
        const parsed = JSON.parse(event.data);
        this.callbacks.onHeartbeat(parsed);
      } catch (err) {

      }
    });

    this.eventSource.onerror = (err) => {

      this.callbacks.onError(err);
    };

    if (this.eventSource.onopen) {
      this.eventSource.onopen = () => {
        if (this.callbacks.onOpen) this.callbacks.onOpen();
      };
    }
  }

  disconnect(): void {
    if (!this.eventSource) return;

    this.eventSource.close();
    this.eventSource = null;
  }
}

export class PollingTransport implements TelemetryTransport {
  private url: string;
  private intervalMs: number;
  private callbacks: Pick<TelemetryTransportCallbacks, "onSnapshot" | "onError">;
  private timer: NodeJS.Timeout | null = null;

  constructor(url: string, intervalMs: number, callbacks: Pick<TelemetryTransportCallbacks, "onSnapshot" | "onError">) {
    this.url = url;
    this.intervalMs = intervalMs;
    this.callbacks = callbacks;
  }

  connect(): void {
    if (this.timer) return;

    const poll = async () => {
      try {
        const res = await fetch(this.url);
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        const json = await res.json();
        // Standard payload wraps in a {"status": "success", "data": {...}} envelope
        if (json.data) {
          this.callbacks.onSnapshot(json.data);
        } else {
          this.callbacks.onSnapshot(json);
        }
      } catch (err) {

        this.callbacks.onError(err);
      }
    };

    // Poll immediately on connect, then schedule interval
    poll();
    this.timer = setInterval(poll, this.intervalMs);
  }

  disconnect(): void {
    if (!this.timer) return;

    clearInterval(this.timer);
    this.timer = null;
  }
}

export interface TelemetryClientCallbacks {
  onStateChange(state: ConnectionState): void;
  onSnapshot(snapshot: TelemetrySnapshotV3): void;
  onError(error: string | null): void;
  onHeartbeat?(hb: any): void;
}

export class TelemetryClient {
  private sseUrl: string;
  private restUrl: string;
  private expectedSchemaVersion: number;

  private sseTransport: SSETransport | null = null;
  private pollingTransport: PollingTransport | null = null;
  private connectionState: ConnectionState = "loading";
  private error: string | null = null;

  private lastSequence = 0;
  private lastBootId: string | null = null;

  private reconnectDelay = 1000;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private callbacks: TelemetryClientCallbacks[] = [];

  constructor(config: { sseUrl: string; restUrl: string; expectedSchemaVersion: number }) {
    this.sseUrl = config.sseUrl;
    this.restUrl = config.restUrl;
    this.expectedSchemaVersion = config.expectedSchemaVersion;
  }

  subscribe(cb: TelemetryClientCallbacks): void {
    this.callbacks.push(cb);
    // Emit initial status to new subscriber
    cb.onStateChange(this.connectionState);
    cb.onError(this.error);
  }

  unsubscribe(cb: TelemetryClientCallbacks): void {
    this.callbacks = this.callbacks.filter((item) => item !== cb);
  }

  private emitStateChange(state: ConnectionState): void {
    this.connectionState = state;
    this.callbacks.forEach((cb) => cb.onStateChange(state));
  }

  private emitError(err: string | null): void {
    this.error = err;
    this.callbacks.forEach((cb) => cb.onError(err));
  }

  private emitSnapshot(snapshot: TelemetrySnapshotV3): void {
    this.callbacks.forEach((cb) => cb.onSnapshot(snapshot));
  }

  start(): void {

    this.emitStateChange("loading");
    this.emitError(null);
    this.connectSSE();
  }

  stop(): void {

    this.disconnectAll();
  }

  private disconnectAll(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.sseTransport) {
      this.sseTransport.disconnect();
      this.sseTransport = null;
    }
    if (this.pollingTransport) {
      this.pollingTransport.disconnect();
      this.pollingTransport = null;
    }
  }

  private connectSSE(): void {
    this.disconnectAll();

    this.sseTransport = new SSETransport(this.sseUrl, {
      onSnapshot: (snapshot) => this.handleSnapshot(snapshot, "sse"),
      onHeartbeat: (hb) => this.handleHeartbeat(hb),
      onError: () => this.handleSSEFailure(),
      onOpen: () => {

      }
    });

    this.sseTransport.connect();
  }

  private handleSnapshot(snapshot: TelemetrySnapshotV3, source: "sse" | "polling"): void {
    const meta = snapshot._meta;
    if (!meta) {

      return;
    }

    // 1. Schema Version Validation
    if (meta.schema_version !== this.expectedSchemaVersion) {
      const errorMsg = `Telemetry schema version mismatch: Expected v${this.expectedSchemaVersion}, got v${meta.schema_version}.`;

      this.emitError(errorMsg);
      this.emitStateChange("failed");
      this.disconnectAll();
      return;
    }

    // 2. Boot ID Change Detection
    if (this.lastBootId && meta.boot_id !== this.lastBootId) {

      this.lastSequence = 0;
    }
    this.lastBootId = meta.boot_id;

    // 3. Monotonic Sequence Ordering Filter
    if (meta.sequence <= this.lastSequence && this.lastSequence > 0) {

      return;
    }
    this.lastSequence = meta.sequence;

    // 4. Update Client State
    this.reconnectDelay = 1000; // Reset reconnect delay on success
    this.emitError(null);
    this.emitSnapshot(snapshot);

    if (source === "sse") {
      this.emitStateChange("connected");
      // If we recovered the SSE connection, we can stop the degraded polling fallback
      if (this.pollingTransport) {

        this.pollingTransport.disconnect();
        this.pollingTransport = null;
      }
    } else if (this.connectionState !== "connected") {
      // If we are getting snapshots via polling, show failed/polling status
      this.emitStateChange("failed");
    }
  }

  private handleHeartbeat(hb: any): void {

    this.callbacks.forEach((cb) => cb.onHeartbeat && cb.onHeartbeat(hb));
    
    // Validate heartbeat schema version
    if (hb && hb.schema_version && hb.schema_version !== this.expectedSchemaVersion) {
      const errorMsg = `Telemetry schema version mismatch on heartbeat: Expected v${this.expectedSchemaVersion}, got v${hb.schema_version}.`;
      this.emitError(errorMsg);
      this.emitStateChange("failed");
      this.disconnectAll();
    }
  }

  private handleSSEFailure(): void {
    // Transition to reconnecting if currently connected
    if (this.connectionState === "connected") {
      this.emitStateChange("reconnecting");
    }

    // Schedule connection retry with exponential backoff (capped at 30s)
    if (!this.reconnectTimer) {

      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connectSSE();
      }, this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
    }

    // Start background REST polling fallback if not already active
    if (!this.pollingTransport && (this.connectionState === "loading" || this.connectionState === "reconnecting")) {

      this.pollingTransport = new PollingTransport(this.restUrl, 30000, {
        onSnapshot: (snapshot) => this.handleSnapshot(snapshot, "polling"),
        onError: (err) => this.emitError(`Telemetry stream offline. Polling update failed: ${err.message || err}`)
      });
      this.pollingTransport.connect();
      this.emitStateChange("failed");
      this.emitError("Real-time stream connection lost. Degraded polling fallback active.");
    }
  }
}

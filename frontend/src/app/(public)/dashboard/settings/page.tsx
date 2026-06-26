import React from "react";
import { Container } from "@/components/layout/Container";
import { PageHeader } from "@/components/layout/PageHeader";

export default function SettingsPage() {
  return (
    <Container className="py-8 max-w-4xl">
      <PageHeader 
        title="Account Settings" 
        description="Manage your account details and personalization preferences."
      />
      
      <div className="mt-8 space-y-6">
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <h3 className="font-semibold text-lg">Profile Information</h3>
          <p className="text-sm text-muted-foreground">
            Account settings will be available in a future update. For now, your personalization data is automatically synced securely.
          </p>
        </div>

        <div className="rounded-lg border bg-card p-6 space-y-4">
          <h3 className="font-semibold text-lg">Data & Privacy</h3>
          <p className="text-sm text-muted-foreground">
            You have full control over your data.
          </p>
          <div className="flex gap-4 pt-2">
            <button className="text-sm text-primary hover:underline font-medium">Export My Data</button>
            <button className="text-sm text-destructive hover:underline font-medium">Clear Browsing History</button>
          </div>
        </div>
      </div>
    </Container>
  );
}

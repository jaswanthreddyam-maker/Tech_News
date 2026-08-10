"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import WelcomeOverlayClient from "./WelcomeOverlayClient";

interface WelcomeOverlayProps {
  children: React.ReactNode;
}

export function WelcomeOverlay({ children }: WelcomeOverlayProps) {
  return <>{children}</>;
}
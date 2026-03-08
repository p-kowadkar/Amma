/**
 * Cloud Brain WebSocket Client — Ch 43-52
 * Connects the phone app to Amma's Cloud Brain server.
 * Sends risk signals, receives voice commands and state updates.
 */

export type EventType =
  | "OBSERVATION"
  | "USER_COMMAND"
  | "PHONE_SIGNAL"
  | "HEARTBEAT"
  | "VOICE_COMMAND"
  | "STATE_UPDATE"
  | "MODE_CHANGE";

export interface AmmaEvent {
  type: EventType;
  device: "laptop" | "phone" | "parent_portal";
  user_id: string;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface AmmaState {
  timepass_seconds: number;
  work_seconds: number;
  warning_level: number;
  in_break: boolean;
  last_classification: string;
  current_mode: string;
  nuclear_count: number;
  phone_risk_level: number;
  laptop_classification: string;
}

type EventHandler = (event: AmmaEvent) => void;

export class CloudBrainClient {
  private ws: WebSocket | null = null;
  private url: string;
  private userId: string;
  private reconnectDelay = 3000;
  private maxReconnectDelay = 30000;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;
  private handlers: Map<EventType, EventHandler[]> = new Map();
  private _connected = false;

  constructor(url: string, userId: string) {
    this.url = url;
    this.userId = userId;
  }

  get connected(): boolean {
    return this._connected;
  }

  connect(): void {
    const wsUrl = `${this.url}/ws/${this.userId}/phone`;
    console.log(`[CloudBrain] Connecting to ${wsUrl}...`);

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("[CloudBrain] Connected!");
        this._connected = true;
        this.reconnectDelay = 3000;
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data: AmmaEvent = JSON.parse(event.data as string);
          this.dispatch(data);
        } catch (e) {
          console.error("[CloudBrain] Parse error:", e);
        }
      };

      this.ws.onclose = () => {
        console.log("[CloudBrain] Disconnected. Reconnecting...");
        this._connected = false;
        this.stopHeartbeat();
        this.scheduleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error("[CloudBrain] Error:", error);
      };
    } catch (e) {
      console.error("[CloudBrain] Connection failed:", e);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._connected = false;
  }

  // ── Send events ────────────────────────────────────────

  /** Send a phone risk signal to Cloud Brain (privacy-safe: only risk_level + category). */
  sendRiskSignal(riskLevel: number, category: string): void {
    this.send({
      type: "PHONE_SIGNAL",
      device: "phone",
      user_id: this.userId,
      timestamp: new Date().toISOString(),
      data: {
        risk_level: Math.max(0, Math.min(5, riskLevel)),
        category, // social | adult | gaming | entertainment | other
      },
    });
  }

  /** Send a user command (break, back, declare_work, etc.). */
  sendCommand(command: string, extra: Record<string, unknown> = {}): void {
    this.send({
      type: "USER_COMMAND",
      device: "phone",
      user_id: this.userId,
      timestamp: new Date().toISOString(),
      data: { command, ...extra },
    });
  }

  // ── Event handlers ─────────────────────────────────────

  on(type: EventType, handler: EventHandler): void {
    const list = this.handlers.get(type) || [];
    list.push(handler);
    this.handlers.set(type, list);
  }

  off(type: EventType, handler: EventHandler): void {
    const list = this.handlers.get(type) || [];
    this.handlers.set(
      type,
      list.filter((h) => h !== handler)
    );
  }

  // ── Internals ──────────────────────────────────────────

  private send(event: AmmaEvent): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(event));
    }
  }

  private dispatch(event: AmmaEvent): void {
    const handlers = this.handlers.get(event.type) || [];
    for (const h of handlers) {
      try {
        h(event);
      } catch (e) {
        console.error(`[CloudBrain] Handler error for ${event.type}:`, e);
      }
    }
  }

  private startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      this.send({
        type: "HEARTBEAT",
        device: "phone",
        user_id: this.userId,
        timestamp: new Date().toISOString(),
        data: {},
      });
    }, 60_000); // Every 60 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private scheduleReconnect(): void {
    setTimeout(() => {
      this.reconnectDelay = Math.min(
        this.reconnectDelay * 1.5,
        this.maxReconnectDelay
      );
      this.connect();
    }, this.reconnectDelay);
  }
}

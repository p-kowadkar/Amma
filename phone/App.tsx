/**
 * Amma Phone App — Ch 43-52
 * Cross-device focus guardian: connects to Cloud Brain,
 * shows session status, receives Amma's voice commands.
 */
import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  StatusBar,
  Alert,
  TextInput,
} from "react-native";
import {
  CloudBrainClient,
  AmmaEvent,
  AmmaState,
} from "./src/services/CloudBrainClient";

// ── Config ───────────────────────────────────────────────────────────────────
const DEFAULT_SERVER = "ws://localhost:8080";
const DEFAULT_USER_ID = "pranav";

// ── Color palette ────────────────────────────────────────────────────────────
const COLORS = {
  bg: "#121218",
  card: "#1E1E2A",
  accent: "#FF8800",
  work: "#4CAF50",
  timepass: "#F44336",
  grey: "#9E9E9E",
  text: "#F0F0F0",
  muted: "#A0A0AA",
  warning: "#FFC107",
};

// ── Warning level colors ─────────────────────────────────────────────────────
function warningColor(level: number): string {
  if (level === 0) return COLORS.work;
  if (level <= 2) return COLORS.warning;
  if (level <= 4) return COLORS.timepass;
  return "#D32F2F";
}

export default function App() {
  const [connected, setConnected] = useState(false);
  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER);
  const [userId, setUserId] = useState(DEFAULT_USER_ID);
  const [showSettings, setShowSettings] = useState(false);
  const [state, setState] = useState<Partial<AmmaState>>({});
  const [messages, setMessages] = useState<
    { text: string; time: string; type: string }[]
  >([]);
  const clientRef = useRef<CloudBrainClient | null>(null);

  // ── Connect to Cloud Brain ─────────────────────────────
  const connectToBrain = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect();
    }

    const client = new CloudBrainClient(serverUrl, userId);

    // Handle state updates
    client.on("STATE_UPDATE", (event: AmmaEvent) => {
      setState(event.data as Partial<AmmaState>);
    });

    // Handle voice commands from Amma
    client.on("VOICE_COMMAND", (event: AmmaEvent) => {
      const text = event.data.text as string;
      const type = (event.data.intervention_type as string) || "info";
      setMessages((prev) => [
        { text, time: new Date().toLocaleTimeString(), type },
        ...prev.slice(0, 49), // Keep last 50
      ]);
      // Show alert for important interventions
      if (type.includes("NUCLEAR") || type.includes("CONTRADICTION")) {
        Alert.alert("Amma", text);
      }
    });

    client.connect();
    clientRef.current = client;

    // Poll connection status
    const interval = setInterval(() => {
      setConnected(client.connected);
    }, 1000);

    return () => {
      clearInterval(interval);
      client.disconnect();
    };
  }, [serverUrl, userId]);

  useEffect(() => {
    const cleanup = connectToBrain();
    return cleanup;
  }, [connectToBrain]);

  // ── Actions ────────────────────────────────────────────
  const sendBreak = () => clientRef.current?.sendCommand("break");
  const sendBack = () => clientRef.current?.sendCommand("back");
  const sendRisk = (level: number, cat: string) =>
    clientRef.current?.sendRiskSignal(level, cat);

  // ── Computed values ────────────────────────────────────
  const workMin = Math.round((state.work_seconds || 0) / 60);
  const timepassMin = Math.round((state.timepass_seconds || 0) / 60);
  const total = workMin + timepassMin || 1;
  const efficiency = Math.round((workMin / total) * 100);
  const warningLevel = state.warning_level || 0;
  const mode = state.current_mode || "GUARD";
  const classification = state.last_classification || "—";

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />

      {/* ── Header ──────────────────────────────────────── */}
      <View style={styles.header}>
        <Text style={styles.title}>Amma \u0905\u092E\u094D\u092E\u093E</Text>
        <TouchableOpacity onPress={() => setShowSettings(!showSettings)}>
          <Text style={styles.settingsBtn}>\u2699\uFE0F</Text>
        </TouchableOpacity>
      </View>

      {/* ── Settings panel ──────────────────────────────── */}
      {showSettings && (
        <View style={styles.settingsPanel}>
          <Text style={styles.settingsLabel}>Cloud Brain URL</Text>
          <TextInput
            style={styles.input}
            value={serverUrl}
            onChangeText={setServerUrl}
            placeholder="ws://localhost:8080"
            placeholderTextColor={COLORS.muted}
          />
          <Text style={styles.settingsLabel}>User ID</Text>
          <TextInput
            style={styles.input}
            value={userId}
            onChangeText={setUserId}
            placeholder="pranav"
            placeholderTextColor={COLORS.muted}
          />
          <TouchableOpacity
            style={styles.connectBtn}
            onPress={connectToBrain}
          >
            <Text style={styles.connectBtnText}>Reconnect</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* ── Connection status ───────────────────────────── */}
      <View style={styles.statusBar}>
        <View
          style={[
            styles.dot,
            { backgroundColor: connected ? COLORS.work : COLORS.timepass },
          ]}
        />
        <Text style={styles.statusText}>
          {connected ? "Connected to Cloud Brain" : "Disconnected"}
        </Text>
        <Text style={styles.modeText}>{mode}</Text>
      </View>

      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* ── Dashboard cards ──────────────────────────── */}
        <View style={styles.cardRow}>
          <View style={[styles.card, { flex: 1, marginRight: 8 }]}>
            <Text style={styles.cardLabel}>Classification</Text>
            <Text
              style={[
                styles.cardValue,
                {
                  color:
                    classification === "WORK"
                      ? COLORS.work
                      : classification === "TIMEPASS"
                      ? COLORS.timepass
                      : COLORS.grey,
                },
              ]}
            >
              {classification}
            </Text>
          </View>
          <View style={[styles.card, { flex: 1, marginLeft: 8 }]}>
            <Text style={styles.cardLabel}>Warning Level</Text>
            <Text
              style={[styles.cardValue, { color: warningColor(warningLevel) }]}
            >
              L{warningLevel}
            </Text>
          </View>
        </View>

        <View style={styles.cardRow}>
          <View style={[styles.card, { flex: 1, marginRight: 8 }]}>
            <Text style={styles.cardLabel}>Work</Text>
            <Text style={[styles.cardValue, { color: COLORS.work }]}>
              {workMin}m
            </Text>
          </View>
          <View style={[styles.card, { flex: 1, marginLeft: 8 }]}>
            <Text style={styles.cardLabel}>Timepass</Text>
            <Text style={[styles.cardValue, { color: COLORS.timepass }]}>
              {timepassMin}m
            </Text>
          </View>
        </View>

        {/* ── Efficiency bar ──────────────────────────── */}
        <View style={styles.card}>
          <Text style={styles.cardLabel}>Efficiency</Text>
          <View style={styles.barBg}>
            <View
              style={[
                styles.barFill,
                {
                  width: `${efficiency}%`,
                  backgroundColor:
                    efficiency >= 70 ? COLORS.work : COLORS.timepass,
                },
              ]}
            />
          </View>
          <Text style={[styles.cardValue, { fontSize: 20 }]}>
            {efficiency}%
          </Text>
        </View>

        {/* ── Quick actions ────────────────────────────── */}
        <View style={styles.cardRow}>
          <TouchableOpacity
            style={[styles.actionBtn, { backgroundColor: COLORS.work }]}
            onPress={sendBreak}
          >
            <Text style={styles.actionText}>\u2615 Break</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.actionBtn, { backgroundColor: COLORS.accent }]}
            onPress={sendBack}
          >
            <Text style={styles.actionText}>\uD83D\uDCAA Back</Text>
          </TouchableOpacity>
        </View>

        {/* ── Risk report (for demo) ──────────────────── */}
        <Text style={styles.sectionTitle}>Report Activity (Demo)</Text>
        <View style={styles.riskRow}>
          {[
            { label: "Work", risk: 0, cat: "work" },
            { label: "Social", risk: 3, cat: "social" },
            { label: "Stream", risk: 4, cat: "entertainment" },
            { label: "Gaming", risk: 3, cat: "gaming" },
          ].map((item) => (
            <TouchableOpacity
              key={item.label}
              style={[
                styles.riskBtn,
                { borderColor: item.risk >= 3 ? COLORS.timepass : COLORS.work },
              ]}
              onPress={() => sendRisk(item.risk, item.cat)}
            >
              <Text style={styles.riskBtnText}>{item.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── Amma messages ───────────────────────────── */}
        <Text style={styles.sectionTitle}>Amma Says</Text>
        {messages.length === 0 && (
          <Text style={styles.emptyText}>
            No messages yet. Amma is watching.
          </Text>
        )}
        {messages.map((msg, i) => (
          <View key={i} style={styles.messageCard}>
            <Text style={styles.messageTime}>{msg.time}</Text>
            <Text style={styles.messageText}>{msg.text}</Text>
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

// ── Styles ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg, paddingTop: 50 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    marginBottom: 8,
  },
  title: { fontSize: 24, fontWeight: "bold", color: COLORS.accent },
  settingsBtn: { fontSize: 22 },
  settingsPanel: {
    backgroundColor: COLORS.card,
    marginHorizontal: 16,
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
  },
  settingsLabel: { color: COLORS.muted, fontSize: 12, marginBottom: 4 },
  input: {
    backgroundColor: COLORS.bg,
    color: COLORS.text,
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
    fontSize: 14,
  },
  connectBtn: {
    backgroundColor: COLORS.accent,
    borderRadius: 8,
    padding: 10,
    alignItems: "center",
  },
  connectBtnText: { color: "#fff", fontWeight: "bold" },
  statusBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 8,
  },
  dot: { width: 8, height: 8, borderRadius: 4, marginRight: 8 },
  statusText: { color: COLORS.muted, fontSize: 13, flex: 1 },
  modeText: { color: COLORS.accent, fontSize: 13, fontWeight: "bold" },
  scroll: { flex: 1, paddingHorizontal: 16 },
  cardRow: { flexDirection: "row", marginBottom: 12 },
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  cardLabel: { color: COLORS.muted, fontSize: 12, marginBottom: 6 },
  cardValue: { color: COLORS.text, fontSize: 28, fontWeight: "bold" },
  barBg: {
    height: 8,
    backgroundColor: "#333",
    borderRadius: 4,
    marginVertical: 8,
    overflow: "hidden",
  },
  barFill: { height: "100%", borderRadius: 4 },
  actionBtn: {
    flex: 1,
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
    marginHorizontal: 4,
  },
  actionText: { color: "#fff", fontSize: 16, fontWeight: "bold" },
  sectionTitle: {
    color: COLORS.text,
    fontSize: 16,
    fontWeight: "bold",
    marginTop: 8,
    marginBottom: 8,
  },
  riskRow: { flexDirection: "row", justifyContent: "space-around", marginBottom: 16 },
  riskBtn: {
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  riskBtnText: { color: COLORS.text, fontSize: 13 },
  emptyText: { color: COLORS.muted, fontSize: 14, textAlign: "center", marginVertical: 20 },
  messageCard: {
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    borderLeftWidth: 3,
    borderLeftColor: COLORS.accent,
  },
  messageTime: { color: COLORS.muted, fontSize: 11, marginBottom: 4 },
  messageText: { color: COLORS.text, fontSize: 14, lineHeight: 20 },
});

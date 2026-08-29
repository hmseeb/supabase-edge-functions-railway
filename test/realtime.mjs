const origin = process.env.SUPABASE_ORIGIN;
const anonKey = process.env.SUPABASE_ANON_KEY;
const serviceKey = process.env.SUPABASE_SERVICE_KEY;
if (!origin || !anonKey || !serviceKey) throw new Error("missing Supabase test environment");

const wsOrigin = origin.replace(/^http/, "ws");
const socket = new WebSocket(`${wsOrigin}/realtime/v1/websocket?apikey=${encodeURIComponent(anonKey)}&vsn=1.0.0`);
const timeout = setTimeout(() => {
  console.error("Realtime change event timed out");
  process.exit(1);
}, 45000);

let inserted = false;
socket.addEventListener("open", () => {
  socket.send(JSON.stringify([
    "1",
    "1",
    "realtime:public:railway_template_proof",
    "phx_join",
    {
      config: {
        broadcast: { ack: false, self: false },
        presence: { key: "" },
        postgres_changes: [{ event: "INSERT", schema: "public", table: "railway_template_proof" }],
      },
      access_token: anonKey,
    },
  ]));
});

socket.addEventListener("message", async (event) => {
  const message = JSON.parse(event.data);
  const eventName = Array.isArray(message) ? message[3] : message.event;
  const payload = Array.isArray(message) ? message[4] : message.payload;
  if (eventName === "phx_reply" && payload?.status === "ok" && !inserted) {
    inserted = true;
    const response = await fetch(`${origin}/rest/v1/railway_template_proof`, {
      method: "POST",
      headers: {
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
        "Content-Type": "application/json",
        Prefer: "return=representation",
      },
      body: JSON.stringify({ value: "realtime-proof" }),
    });
    if (!response.ok) throw new Error(`Realtime trigger insert failed: ${response.status}`);
  }
  if (eventName === "postgres_changes" && payload?.data?.record?.value === "realtime-proof") {
    clearTimeout(timeout);
    socket.close();
    console.log("ok: Realtime received database insert");
  }
});

socket.addEventListener("error", () => {
  clearTimeout(timeout);
  console.error("Realtime WebSocket failed");
  process.exit(1);
});

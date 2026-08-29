const origin = process.env.SUPABASE_ORIGIN;
const anonKey = process.env.SUPABASE_ANON_KEY;
const serviceKey = process.env.SUPABASE_SERVICE_KEY;
if (!origin || !anonKey || !serviceKey) throw new Error("missing Supabase test environment");

const table = "railway_template_proof";
const topic = `realtime:public:${table}`;
const wsOrigin = origin.replace(/^http/, "ws");
const socket = new WebSocket(
  `${wsOrigin}/realtime/v1/websocket?apikey=${encodeURIComponent(serviceKey)}&vsn=1.0.0`,
);

const fail = (message) => {
  console.error(message);
  process.exit(1);
};
const timeout = setTimeout(() => fail("Realtime change event timed out"), 45000);

let ref = 0;
const send = (event, payload) =>
  socket.send(JSON.stringify({ topic, event, payload, ref: String(++ref) }));

let inserted = false;
socket.addEventListener("open", () => {
  send("phx_join", {
    config: {
      broadcast: { ack: false, self: false },
      presence: { key: "" },
      postgres_changes: [{ event: "INSERT", schema: "public", table }],
    },
    access_token: serviceKey,
  });
});

socket.addEventListener("message", async (event) => {
  const { event: name, payload } = JSON.parse(event.data);

  if (name === "phx_reply" && payload?.status === "error") {
    clearTimeout(timeout);
    fail(`Realtime rejected the subscription: ${JSON.stringify(payload.response)}`);
  }

  // Wait for the Postgres subscription itself, not just the channel join:
  // inserting between those two moments loses the change event.
  const subscribed =
    name === "system" &&
    payload?.status === "ok" &&
    payload?.extension === "postgres_changes";

  if (subscribed && !inserted) {
    inserted = true;
    const response = await fetch(`${origin}/rest/v1/${table}`, {
      method: "POST",
      headers: {
        apikey: serviceKey,
        Authorization: `Bearer ${serviceKey}`,
        "Content-Type": "application/json",
        Prefer: "return=representation",
      },
      body: JSON.stringify({ value: "realtime-proof" }),
    });
    if (!response.ok) {
      clearTimeout(timeout);
      fail(`Realtime trigger insert failed: ${response.status}`);
    }
  }

  if (name === "postgres_changes" && payload?.data?.record?.value === "realtime-proof") {
    clearTimeout(timeout);
    socket.close();
    console.log("ok: Realtime received database insert");
  }
});

socket.addEventListener("error", () => {
  clearTimeout(timeout);
  fail("Realtime WebSocket failed");
});

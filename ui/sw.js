self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : JSON.parse(event.data.text()); } catch { data = { title: "Weather Alert", body: event.data ? event.data.text() : "" }; }
  const title = data.title || "🚨 Weather Alert";
  const body = data.body || "IMD warning for your district — tap to see details";
  const url = data.url || "/alerts.html";
  const severity = (data.severity || "orange").toLowerCase();
  const icon = data.icon || "/weathergpt.png";
  const badge = data.badge || "/weathergpt.png";
  const vibrate = data.vibrate || [200, 100, 200, 100, 200];
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      ...(icon ? {icon} : {}),
      ...(badge ? {badge} : {}),
      vibrate,
      requireInteraction: data.requireInteraction ?? true,
      data: { url },
      actions: data.actions || [{action:"open", title:"View in WeatherGPT"}, {action:"dismiss", title:"Dismiss"}],
      tag: `weather-alert-${severity}`
    })
  );
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  if (event.action === "dismiss") return;
  const url = event.notification.data?.url || "/alerts.html";
  event.waitUntil(clients.openWindow(url));
});

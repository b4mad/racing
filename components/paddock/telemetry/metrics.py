from prometheus_client import Gauge

driver_total = Gauge("driver_total", "number of drivers")
session_total = Gauge("session_total", "number of sessions")

from prometheus_client import Gauge

drivers = Gauge("paddock_drivers_total", "total number of drivers seen")
coaches = Gauge("paddock_coaches_total", "total number of coaches enabled")
social_accounts = Gauge("paddock_social_accounts_total", "total number of social accounts created")
loggedin_drivers = Gauge("paddock_loggedin_drivers_total", "total number of logged in drivers", ["username"])

# k6 tests

[install xk6](https://github.com/grafana/xk6/#install-xk6) and `xk6 build v0.46.0 --with github.com/grafana/xk6-dashboard --with github.com/szkiba/xk6-dotenv` it will place a `k6` binary in your current directory.

## Run tests

```bash
./k6 run --out dashboard -e SUT_HOSTNAME=paddock.b4mad.racing components/paddock/k6.d/smoke.js
```

and head over to <http://127.0.0.1:5665> to see the results.

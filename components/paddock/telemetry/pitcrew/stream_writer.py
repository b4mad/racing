import pathway as pw

class InputSchema(pw.Schema):
    value: int


t = pw.io.csv.read(
    './sum_input_data/',
    schema=InputSchema,
    mode="streaming"
)
t = t.reduce(sum=pw.reducers.sum(t.value))
pw.io.csv.write(t, "output_stream.csv")
pw.run()

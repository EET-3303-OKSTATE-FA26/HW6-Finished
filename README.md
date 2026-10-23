# HW6_FA26

EET 3303, Fall 2026: multithreaded electronic-circuit production simulation.

## Run

Use Python 3.10 or later:

```text
python -m pip install -r requirements.txt
python main.py
```

Enter `begin` to start the five assembly workers, assembly overseer, and three
testing workers. Enter `halt` to stop production and finish testing circuits
already assembled. `inventory` prints the boxed-circuit inventory;
`report` prints cumulative good and bad circuit totals, the circuit IDs and
assembly workers for failed circuits, and the combined average time to produce,
test, and package a circuit. Enter `graph` to open a bar chart of the failure
rate per assembly worker; close the chart window to return to the command
prompt. `spotcheck` prompts for an inspector, box number, and circuit ID. You
can also
provide those values on one line, for example `spotcheck Inspector-1 1 3`;
use a circuit ID listed by `inventory`. Enter `exit` to stop and close the
simulation.

Assembly, testing, packaging, and synchronization for inspector marks are
active. Packaging workers group passing circuits by inspector into boxes of
five; partial boxes remain unboxed when production halts.

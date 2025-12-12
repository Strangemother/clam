# backbone

+ Is a mesh backbone for all bots
+ with a register
+ And an endpoint to inspect concurrent tasks and bots
+ has routing strategy

all units need to be aware of other units. When they wake, a unit emits a
message to register itself (atexit to emit close).

When the internal task changes, such as _making a memory_, the status is applied to
this backbone

When the thinker queries on current tasks, the llm can receive a list of these states,
confidentally stating "I'm thinking of x"

---

When registered, units can announce their dependencies. The backbone stores the
graph, allowing a unit to _ask_ where an output message should be sent.
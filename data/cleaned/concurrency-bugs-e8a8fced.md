<!-- Concurrency bugs.pptx -->

<!-- slide 1 -->
- Concurrency Bugs

<!-- slide 2 -->
# Bugs in concurrent programs

- Writing multi-threaded programs is tricky
- Bugs are non-deterministic and occur based on execution order of threads – very hard to debug
- Two types of bugs
  - Deadlocks: threads cannot execute any further and wait for each other
  - Non-deadlock bugs: non deadlock but incorrect results when threads execute

<!-- slide 3 -->
# Non deadlock bugs

- Atomicity bugs – atomicity assumptions made by programmer are violated during execution of concurrent threads
  - Fix: locks for mutual exclusion
- Order-violation bugs – desired order of memory accesses is flipped during concurrent execution
  - Fix: condition variables

<!-- slide 4 -->
# Atomicity bug: example

- One thread reads and prints a shared data item, while another concurrently modifies it
- Atomicity bugs can occur, not just when writing to shared data, but even when reading it

<!-- slide 5 -->
# Atomicity bug example: fix

- Always use locks when accessing shared data

<!-- slide 6 -->
# Order violation bug: example

- Thread1 assumes Thread2 has already run
- No assumptions can be made on order of execution of concurrent threads

<!-- slide 7 -->
# Ordering violation bug example: fix

- Use condition variables or semaphores

<!-- slide 8 -->
# Deadlock bugs

- Classic example: Thread1 holds lock L1 and is waiting for lock L2. Thread2 holds L2 and is waiting for L1.
- Deadlock need not always occur. Only occurs if executions overlap and context switch from a thread after acquiring only one lock.

<!-- slide 9 -->
# Deadlock: a visual representation

- Cycle in a dependency graph

<!-- slide 10 -->
# Conditions for deadlock

- Mutual exclusion: a thread claims exclusive control of a resource (e.g., lock)
- Hold-and-wait: thread holds a resource and is waiting for another
- No preemption: thread cannot be made to give up its resource (e.g., cannot take back a lock)
- Circular wait: there exists a cycle in the resource dependency graph
- ALL four of the above conditions must hold for a deadlock to occur

<!-- slide 11 -->
# Preventing circular wait

- Acquire locks in a certain fixed order
  - E.g., both threads acquire L1 before L2
- Total ordering (or even a partial ordering on related locks) must be followed
  - E.g., order locks by address of lock variable

<!-- slide 12 -->
# Preventing hold-and-wait

- Acquire all locks at once, say, by acquiring a master lock first
- But this method may reduce concurrent execution and performance gains

<!-- slide 13 -->
# Other solutions to deadlocks

- Deadlock avoidance: if OS knew which process needs which locks, it can schedule the processes in that deadlock will not occur
  - Banker’s algorithm is very popular, but impractical in real life to assume this knowledge
  - Example, below are locks needed by threads and a possible schedule decided by OS
- Detect and recover: reboot system or kill deadlocked processes
- 13

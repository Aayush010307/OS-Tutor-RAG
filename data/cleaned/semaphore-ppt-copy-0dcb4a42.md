<!-- Semaphore.ppt - Copy.pptx -->

<!-- slide 1 -->
- Semaphores

<!-- slide 2 -->
# What is a semaphore?

- Synchronization primitive like condition variables

```
Semaphore is a variable with an underlying counter
```

- Two functions on a semaphore variable
  - Up/post increments the counter
  - Down/wait decrements the counter and blocks the calling thread if the resulting value is negative
- A semaphore with init value 1 acts as a simple lock (binary semaphore = mutex)

<!-- slide 3 -->
# Semaphores for ordering

- Can be used to set order of execution between threads like CV
- Example: parent waiting for child (init = 0)

<!-- slide 4 -->
# Example: Producer/Consumer (1)

- Need two semaphores for signaling
  - One to track empty slots, and make producer wait if no more empty slots
  - One to track full slots, and make consumer wait if no more full slots
- One semaphore to act as mutex for buffer

<!-- slide 5 -->
# Example: Producer/Consumer (2)

<!-- slide 6 -->
# Incorrect solution with deadlock

- What if lock is acquired before signaling?
- Waiting thread sleeps with mutex and the signaling thread can never wake it up

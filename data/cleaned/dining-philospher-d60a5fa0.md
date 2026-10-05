<!-- dining philospher.pdf -->

<!-- page 1 -->
FIRST ATTEMPT:

```
#DEFINE N5
Void philosopher (int i)
{
While true
{
Think (); // for some time
Take_fork (Ri)
Take_fork (Li)
Eat ();
Put_fork (Li)
Put_fork (Ri)
}
}
```

SECOND ATTEMPT:

```
#DEFINE N5
Void philosopher (int i)
{
While true
{
Think ();
Take_fork (Ri)
If (available (Li)
{
Take_fork (Li)
Eat ();
Put_fork (Ri)
Put_fork (Li)
}
```

<!-- page 2 -->
```
Else
{
Put_fork (Ri)
Sleep (T)
}
}
```

In the solution two instead of sleep we can change to sleep (random_time), still is not guarantee that the starvation will not occur.

THIRD ATTEMPT:

```
#DEFINE N5
Void philosopher (int i)
{
While true
{
Think ();
Lock (mutex)
Take_fork (Ri)
Take_fork (Li)
Eat ();
Put_fork (Li)
Put_fork (Ri)
Unlock (mutex)
}
}
```

<!-- page 3 -->
FOURTH ATTEMPT USING SEMAPHORES

```
Void philosopher (int i)
                                        void take_forks (int i)
                                        void put_forks (int i)
{
                                        {
                                        lock(mutex)
While (TRUE)
                                        lock (mutex);
                                        state [i] = THINKING
{
                                        state [i] = HUNGRY
                                        test (LEFT)
Think ();
                                        test (i);
                                        test (RIGHT)
Take_forks (i);
                                       unlock (mutex)
                                        unlock (mutex);
Eat ();
                                        down (s[i])
                                        }
```

Put_forks (); }

```
}
}
Void test (int i)
{
```

If (state [i] = HUNGRY && state [LEFT]! = EATING && state [RIGHT]! = EATING)

```
{
State [i] = EATING
UP (S[i]);
}
}
```

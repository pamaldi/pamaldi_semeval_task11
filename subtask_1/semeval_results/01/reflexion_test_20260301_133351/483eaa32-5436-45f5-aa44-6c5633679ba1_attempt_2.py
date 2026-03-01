% COUNTEREXAMPLE: Build a model where premises are TRUE but conclusion is FALSE

% Witness: odd number that is negative
odd(-3).
negative(-3).

% Witnesses for prime numbers that are negative
prime(-2).
negative(-2).

% Additional prime number that is NOT odd
prime(-2).  % -2 is prime and even

% Fail clause for non-witness primes and odds
odd(_) :- fail.
prime(_) :- fail.

% Validity check: "Some prime numbers are odd numbers" should FAIL in this model
valid_syllogism :- prime(X), odd(X).
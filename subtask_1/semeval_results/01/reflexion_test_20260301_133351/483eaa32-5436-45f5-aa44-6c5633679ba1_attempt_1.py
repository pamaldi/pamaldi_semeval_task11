% Witness: an odd number that is a negative number
odd(-3).
negative(-3).

% Another witness: a prime number that is a negative number
prime(-3).

% Rule from "A portion of the prime numbers are negative numbers"
% (We already have -3 as a prime and negative number)

% Validity check: "Some prime numbers are odd numbers"
valid_syllogism :- prime(X), odd(X).
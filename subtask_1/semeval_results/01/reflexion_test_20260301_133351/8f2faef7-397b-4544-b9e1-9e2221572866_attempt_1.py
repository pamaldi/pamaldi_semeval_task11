% Witness: a celebrity who is a politician but NOT a prime minister (counterexample)
celebrity(john).
politician(john).

% prime minister has NO facts in this model
prime_minister(_) :- fail.

% Rule from first premise
politician(X) :- prime_minister(X).

% Validity check: Some celebrity is a prime minister
valid_syllogism :- celebrity(X), prime_minister(X).
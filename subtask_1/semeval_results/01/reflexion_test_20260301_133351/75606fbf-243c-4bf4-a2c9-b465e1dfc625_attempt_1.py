% Witness: a man who is also a human and thus a primate
man(john).
human(john).

% Rule: Every human is a primate
primate(X) :- human(X).

% Rule: Any man is a human
human(X) :- man(X).

% Validity check: Every man is a primate
valid_syllogism :- \+ (man(X), \+ primate(X)).
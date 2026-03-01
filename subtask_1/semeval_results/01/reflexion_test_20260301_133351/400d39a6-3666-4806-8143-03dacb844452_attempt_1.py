% Facts
scientist(alice).
scientist(bob).

% physicists (empty)
physicist(_) :- fail.

% Rules
academic(X) :- scientist(X).

% Validity check
valid_syllogism :- \+ (academic(X), physicist(X)).
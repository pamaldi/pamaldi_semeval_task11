% Fail clause: No mammals are rational beings
mammal(_) :- fail.

% Fail clause: No humans are rational beings (will be overridden by facts)
rational_being(_) :- fail.

% Facts: humans who are rational beings
human(socrates).
rational_being(socrates).

% Validity check: No mammal is a human
valid_syllogism :- \+ (mammal(X), human(X)).
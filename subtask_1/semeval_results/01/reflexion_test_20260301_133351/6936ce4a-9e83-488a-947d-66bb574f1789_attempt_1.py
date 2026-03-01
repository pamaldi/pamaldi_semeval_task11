% Fail clauses for empty predicates
european(_) :- fail.
north_american(_) :- fail.
french(_) :- fail.

% E-premise: No North American is a European
conflict :- north_american(X), european(X).

% E-premise: No French is a North American
conflict :- french(X), north_american(X).

% Validity check: No French is a European
valid_syllogism :- \+ (french(X), european(X)).
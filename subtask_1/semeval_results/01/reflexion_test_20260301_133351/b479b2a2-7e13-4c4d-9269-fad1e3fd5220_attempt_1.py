% Witnesses for spoons
spoon(s1).
spoon(s2).

% Witnesses for implements
implement(s1).   % s1 is both a spoon and implement
implement(i1).   % i1 is an implement that is NOT a spoon

% Objects have no overlap with spoons
object(X) :- fail.

% Validity check: Some implements are not objects
valid_syllogism :- implement(X), \+ object(X).
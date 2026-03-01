% Facts (witnesses)
oak(western_white).

% Rules from premises
tree(X) :- oak(X).
has_leaves(X) :- tree(X).

% Validity check: All oaks have leaves
valid_syllogism :- \+ (oak(X), \+ has_leaves(X)).
% Witness: a tiger that is a cat
tiger(fluffy).
cat(fluffy).

% Rule from first premise: All cats are fish
fish(X) :- cat(X).

% I-conclusion: Some tigers are fish
valid_syllogism :- tiger(X), fish(X).
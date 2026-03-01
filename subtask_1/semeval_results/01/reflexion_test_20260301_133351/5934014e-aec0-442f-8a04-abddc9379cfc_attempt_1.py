% Facts (witnesses or counterexample entities)
tulip(t1).
rose(r1).

% Fail clauses ONLY for predicates with NO facts and NO rules
% No predicates with fail needed in this case

% Rules from premises
flower(X) :- rose(X).
flower(X) :- tulip(X).

conflict :- tulip(X), rose(X).

% Validity check
valid_syllogism :- tulip(X), flower(X).
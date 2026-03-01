% Facts (witnesses or counterexample entities)
tulip(t1).
rose(r1).

% Fail clauses ONLY for predicates with NO facts and NO rules
% No predicates with fail needed in this case

% Rules from premises
flower(X) :- rose(X).
flower(X) :- tulip(X).

conflict :- tulip(X), rose(X).

% Validity check - this is an INVALID syllogism (undistributed middle)
% We are proving it's invalid by showing a model where premises are true but conclusion is false
% In this case, there is no conclusion to check - the syllogism has no valid conclusion
valid_syllogism :- false.
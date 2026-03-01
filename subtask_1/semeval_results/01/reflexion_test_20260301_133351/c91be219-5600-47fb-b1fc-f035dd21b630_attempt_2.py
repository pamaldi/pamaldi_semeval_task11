% Witness: an athlete
athlete(john).
person(john).

% Rule from first premise: No athletes are lazy
conflict :- athlete(X), lazy(X).

% Validity check: Conclusion is "Some people are lazy"
valid_syllogism :- person(X), lazy(X).
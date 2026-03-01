% Facts: Some people are athletes
person(john).
athlete(john).

% Rule: No athletes are lazy
conflict :- athlete(X), lazy(X).

% Validity check: Conclusion is "Some people are lazy"
valid_syllogism :- person(X), lazy(X).
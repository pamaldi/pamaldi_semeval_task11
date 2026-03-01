% This syllogism is INVALID due to an undistributed middle.
% The premises only establish that:
% 1. All chairs are NOT living things
% 2. All living things are NOT inanimate (i.e., all living things are animate)
% The conclusion claims "Some inanimate objects are not chairs"
% We'll create a counterexample where the premises are true but the conclusion is false

% We need a world where:
% 1. No chair is a living thing
% 2. No living thing is inanimate (i.e., all living things are animate)
% 3. BUT: All inanimate objects ARE chairs (making the conclusion "Some inanimate objects are not chairs" false)

% Facts for the categories
chair(table1).
chair(floor1).  % All inanimate objects are chairs in our counterexample

% Fail clause for empty predicate
inanimate(_) :- fail.  % We'll override this with chair facts

% Rules from premises
% "The category of chairs and the category of living things do not overlap."
conflict :- chair(X), living(X).

% "The group of living things and the group of inanimate objects are mutually exclusive."
conflict :- living(X), inanimate(X).

% Validity check: "A portion of inanimate objects are not chairs" should be FALSE in our counterexample
valid_syllogism :- inanimate(X), \+ chair(X).  % This should fail to show the syllogism is INVALID
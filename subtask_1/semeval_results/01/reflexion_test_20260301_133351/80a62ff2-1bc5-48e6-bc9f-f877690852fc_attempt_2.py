% This syllogism is INVALID - it contains contradictory premises
% Case A: We need to build a COUNTEREXAMPLE where premises are TRUE but conclusion is FALSE

% Let's define entities:
% We need an orange that is NOT a round citrus peel
orange(not_round_citrus).

% But we also need every fruit to be an orange
fruit(not_round_citrus).

% Rule: All fruits are round citrus peels (except our specific counterexample)
% Since we have a counterexample, this rule won't cover all cases
round_citrus_peel(X) :- fruit(X), X \= not_round_citrus.

% Rule: All fruits are oranges
orange(X) :- fruit(X), X \= not_round_citrus.

% Validity check: Does the contradiction actually exist?
% In this counterexample, the premises are all true but the contradiction doesn't occur
% Because our counterexample orange is also a fruit, and the rule about fruits being round citrus peels
% has an exception built in

valid_syllogism :- 
    fruit(not_round_citrus), 
    orange(not_round_citrus), 
    \+ round_citrus_peel(not_round_citrus).
% Let's create a counterexample where the first two premises are true but the third is false

% Some oranges are not round citrus peels (O-premise)
orange(not_round).
% This specific orange is NOT a round citrus peel (I-premise witness)
% No need for explicit rule since we need it to be false

% All fruits are round citrus peels (A-premise)
% Create a fruit that IS a round citrus peel
fruit(citrus_ball).
round_citrus_peel(citrus_ball).

% But now we need to make sure this fruit is NOT an orange
% This makes the third premise "All fruits are oranges" false

% Validity check: The syllogism is invalid if we can show the premises cannot all be true
% We'll check if all three premises can be true simultaneously

% Premise 1: All fruits are round citrus peels
% Premise 2: Some oranges are not round citrus peels
% Premise 3: All fruits are oranges

% If the syllogism were valid, these premises would all be true
% But they cannot all be true - if all fruits are oranges and all fruits are round citrus peels,
% then all oranges would have to be round citrus peels (contradicting premise 2)

valid_syllogism :- 
    % Check if we have a fruit that's not an orange
    \+ (fruit(X), orange(X)),
    % Check if we have an orange that's not a round citrus peel
    orange(not_round),
    \+ round_citrus_peel(not_round).
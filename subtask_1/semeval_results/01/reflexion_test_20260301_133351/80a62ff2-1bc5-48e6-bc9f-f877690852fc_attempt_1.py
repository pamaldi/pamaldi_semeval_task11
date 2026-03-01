% Facts for witness (orange that is NOT a round object with citrus peel)
orange(not_round_citrus).
fruit(not_round_citrus).

% Rules from premises
% All fruits are round objects with citrus peel
% We encode this as: if X is a fruit, then X is a round object with citrus peel
round_citrus_peel(X) :- fruit(X), X \= not_round_citrus.

% Every single fruit is an orange
% We encode as: if X is a fruit, then X is an orange
orange(X) :- fruit(X).

% Validity check: At least one orange is NOT a round object with citrus peel
valid_syllogism :- orange(X), \+ round_citrus_peel(X).
% Facts (witnesses)
statue(david).

% Rule from A-premise: All statues are stones
stone(X) :- statue(X).

% Rule from A-premise: All stones are animate (i.e., never inanimate)
% We encode this as: if something is a stone, it is not inanimate
inanimate(_) :- fail. % No stone is inanimate

% Validity check for conclusion: No statue is inanimate
valid_syllogism :- \+ (statue(X), inanimate(X)).
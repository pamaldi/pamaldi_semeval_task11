% Witness: Canada is a country not a state
country(canada).
% USA state (witness)
state_in_usa(california).

% Fail clause for states_in_usa that are Canada
state_in_usa(canada) :- fail.

% Rule from A-premise: Every Canada is a country
country(X) :- canada(X).

% Fail clause for USA state that is Canada (E-premise)
conflict :- state_in_usa(X), canada(X).

% Validity check: Some countries are not states in USA
valid_syllogism :- country(X), \+ state_in_usa(X).
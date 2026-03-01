% Witness: Amazon River is a river that flows towards the sea
river(amazon).
flows_towards_sea(amazon).

% Rule from A-premise: All rivers flow towards the sea
flows_towards_sea(X) :- river(X).

% I-conclusion check: Some river flows towards the sea
valid_syllogism :- river(X), flows_towards_sea(X).
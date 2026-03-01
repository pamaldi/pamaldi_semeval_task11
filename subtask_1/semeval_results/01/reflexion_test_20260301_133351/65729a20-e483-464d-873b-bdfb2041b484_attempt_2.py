% Facts for iron and metal
iron(iron1).
metal(iron1).

% No metals are a gas (E proposition)
conflict :- metal(X), gas(X).

% Every piece of iron is a metal (A proposition)
metal(X) :- iron(X).

% Gas has no facts, so define it with a fail clause
gas(_) :- fail.

% Validity check: All iron is a gas (A proposition)
valid_syllogism :- \+ (iron(X), \+ gas(X)).
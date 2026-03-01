% Facts (witnesses)
pen(pen1).
writing_instrument(pen1).

% Rules from premises
tool(X) :- writing_instrument(X).

% Validity check
valid_syllogism :- pen(X), tool(X).
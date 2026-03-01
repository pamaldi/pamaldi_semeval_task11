% Facts: some hammers are tools
hammer(claw_hammer).
tool(claw_hammer).

% Rules: anything that is a hammer is an instrument
instrument(X) :- hammer(X).

% Validity check: some tools are instruments
valid_syllogism :- tool(X), instrument(X).
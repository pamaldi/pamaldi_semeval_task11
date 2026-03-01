% COUNTEREXAMPLE: Build a world where:
% 1. Some scientists are not physicists (O-premise)
% 2. All scientists are academics (A-premise)
% 3. But NOT all academics are physicists (so conclusion is false)

% Scientists who are not physicists (O-premise satisfies this)
scientist(alice).
% alice is NOT a physicist (no physicist(alice) fact)

% Another scientist who is a physicist (important for the A-premise)
scientist(bob).
physicist(bob).

% All scientists are academics (A-premise)
academic(X) :- scientist(X).

% Some academics are physicists (bob), some are not (alice)
% This shows conclusion "All academics are physicists" is FALSE

% Physicist predicate has at least one fact (bob), so no fail clause needed
% Academic is defined through rule, so no need for additional facts either

% Validity check: The conclusion is "All academics are physicists"
% If this syllogism were valid, this check would succeed
% But we're showing it's INVALID by building a counterexample
valid_syllogism :- \+ (academic(X), \+ physicist(X)).  % Should FAIL → INVALID
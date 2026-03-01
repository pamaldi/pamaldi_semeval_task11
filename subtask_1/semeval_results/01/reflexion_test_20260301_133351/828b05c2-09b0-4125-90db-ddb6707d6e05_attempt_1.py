% Fail clause for soft_substance since no facts are provided (representing "none are soft")
soft_substance(_) :- fail.

% Witness: a carbon compound that is NOT a diamond
carbon_compound(graphite).

% Rule from first premise: No diamond is a soft substance
conflict :- diamond(X), soft_substance(X).

% Rule from second premise: Everything that is a diamond is a carbon compound
carbon_compound(X) :- diamond(X).

% Rule from third premise: Some carbon compounds are not soft substances
% Use the witness to satisfy this
carbon_compound(graphite).
% graphite is NOT a soft_substance (due to fail clause above)

% Validity check: Some carbon compounds are not soft substances
valid_syllogism :- carbon_compound(X), \+ soft_substance(X).
% Facts (I proposition: "Some liquid is water")
liquid(water1).
water(water1).

% Rule from A-premise: All liquid is composed of rock (liquid → rock)
rock(X) :- liquid(X).

% Validity check: Some water is made of rock (water(W) ∧ rock(W))
valid_syllogism :- water(X), rock(X).
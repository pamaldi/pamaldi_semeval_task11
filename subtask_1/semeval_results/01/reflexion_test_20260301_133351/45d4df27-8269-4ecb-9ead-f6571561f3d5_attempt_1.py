% Facts (witnesses)
spoon(s1).
utensil(s1).
kitchen_tool(s1).

% Rules from premises
% "There is at least one spoon that is a kitchen tool" is already expressed by the fact.
% "Some of the utensils are spoons" is already expressed by the fact.

% Validity check: "Some of the utensils are kitchen tools"
valid_syllogism :- utensil(X), kitchen_tool(X).
% COUNTEREXAMPLE: Utensils and kitchen tools are disjoint sets.
% All spoons that are kitchen tools are NOT utensils.
% Some utensils are spoons (which are kitchen tools), but we will show the conclusion is not necessarily true.

% Witness for "Some of the utensils are spoons"
utensil(utensil1).
spoon(utensil1).

% Witness for "There is at least one spoon that is a kitchen tool"
spoon(utensil1).
kitchen_tool(utensil1).

% Some other utensils that are NOT kitchen tools (this is the key to invalidity)
utensil(utensil2).
% No kitchen_tool fact for utensil2

% Validity check: "Some of the utensils are kitchen tools"
% Should FAIL in this counterexample to show syllogism is INVALID
valid_syllogism :- utensil(X), kitchen_tool(X).
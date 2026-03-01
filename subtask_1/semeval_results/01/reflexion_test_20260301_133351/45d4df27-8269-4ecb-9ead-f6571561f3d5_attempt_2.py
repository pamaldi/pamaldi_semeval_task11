% COUNTEREXAMPLE: Some utensils are spoons (utensil1), which is a kitchen tool.
% BUT: There are other utensils (utensil2) that are NOT kitchen tools.
% This shows the syllogism is INVALID.

% Witness for I-premise "Some of the utensils are spoons"
utensil(utensil1).
spoon(utensil1).

% Witness for I-premise "There is at least one spoon that is a kitchen tool"
spoon(utensil1).
kitchen_tool(utensil1).

% Additional utensil that is NOT a kitchen tool (counterexample)
utensil(utensil2).

% Validity check: "Some of the utensils are kitchen tools"
% Should FAIL in this counterexample
valid_syllogism :- utensil(X), kitchen_tool(X).
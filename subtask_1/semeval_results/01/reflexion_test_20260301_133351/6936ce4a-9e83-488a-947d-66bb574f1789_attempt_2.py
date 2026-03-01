% This syllogism is INVALID (two negative premises with no valid conclusion)
% We need to build a COUNTEREXAMPLE where:
% 1. No North American is a European (premise 1)
% 2. No French is a North American (premise 2)
% 3. But some French person IS a European (conclusion is false)

% Create disjoint sets for North Americans and Europeans
north_american(john).         % John is North American
european(marie).              % Marie is European

% Ensure they are distinct (no overlap between groups)
% Create a French person who IS a European (counterexample)
french(marie).                % Marie is French and European

% E-premise: No North American is a European
conflict1 :- north_american(X), european(X).

% E-premise: No French is a North American
conflict2 :- french(X), north_american(X).

% Validity check: Some French person is a European (conclusion is false)
valid_syllogism :- french(X), european(X).
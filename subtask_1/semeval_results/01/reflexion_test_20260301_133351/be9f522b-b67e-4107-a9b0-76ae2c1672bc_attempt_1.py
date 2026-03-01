% Facts (witnesses)
root_vegetable(carrot1).
carrot(carrot1).

% Rule from second premise: Everything that is a carrot is also a vegetable
vegetable(X) :- carrot(X).

% Validity check: There are vegetables that are root vegetables
valid_syllogism :- vegetable(X), root_vegetable(X).
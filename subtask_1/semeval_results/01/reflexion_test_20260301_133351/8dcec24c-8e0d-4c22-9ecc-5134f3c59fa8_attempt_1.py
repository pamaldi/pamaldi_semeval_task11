% Oak tree witness
oak_tree(ancient_oak).

% Rule from A-premise: All oak trees are plants
plant(X) :- oak_tree(X).

% E-premise constraint: No plant is an animal
conflict :- plant(X), animal(X).

% animal has no facts
animal(_) :- fail.

% Validity check: Conclusion "All oak trees are animals" would mean no oak tree is NOT an animal
valid_syllogism :- \+ (oak_tree(X), \+ animal(X)).
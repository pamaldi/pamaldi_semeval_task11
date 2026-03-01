% Facts for the I-proposition: Some fruits are apples (witness)
fruit(apple1).
apple(apple1).

% Fail clause for "any fruit is a thing that grows on a tree"
% (i.e., "No fruit grows on a tree" → E-proposition)
grows_on_tree(_) :- fail.

% Validity check: Some apples do not grow on trees (O-conclusion)
valid_syllogism :- apple(X), \+ grows_on_tree(X).
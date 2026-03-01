% Witness: an insect that is NOT a spider (to satisfy the conclusion)
insect(ant).

% Rule for "Everything that is a spider is an arachnid"
% (We don't need to define spider/1 or arachnid/1 unless we have facts)
arachnid(X) :- spider(X).

% Fail clause for "Nothing that is an insect is an arachnid"
% (We must define spider/1 to avoid using undefined predicate)
spider(_) :- fail.  % No spiders exist
arachnid(_) :- fail.  % No arachnids exist (except those defined via spider/1)

% Validity check: "It is not the case that all insects are spiders"
% This is equivalent to "There exists an insect that is not a spider"
valid_syllogism :- insect(X), \+ spider(X).
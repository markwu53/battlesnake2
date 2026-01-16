a = [i for i in range(49)]
a = [i*i for i in a]
a = [i % 49 for i in a]
print(a)
a = sorted(list(set(a)))
print(a)
a = [i%7 for i in a]
print(a)

# a = [i for i in range(7*7*7)]
# a = [i*i for i in a]
# a = [i % (7*7*7) for i in a]
# a = sorted(list(set(a)))
# a = [i%7 for i in a]
# print(a)



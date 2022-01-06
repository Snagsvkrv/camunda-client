# Changelog

## 0.8.0

- `Variables.__getitem__` will now throw a `KeyError` when a key cannot be found; use `Variables.get_variable` for optional variables.
- Added  `Variables.__contains__` for `"key" in variables` checks 
 
## 0.7.0 

This is the first PyPI release of `avikom-camunda-client`

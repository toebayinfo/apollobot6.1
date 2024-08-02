#!/bin/bash

# Start the Hypercorn server
hypercorn app:app --bind 0.0.0.0:8000

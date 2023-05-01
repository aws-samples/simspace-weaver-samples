#! /usr/bin/python3

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# SimSpace Weaver Controller
# Implements a class to control the state of a simulation
# Can be called via commandline (main) or as a Lambda function
# Main will start the app and clock, then take a snapshot
# Expects one environment variable to be set:
#   SNAPSHOTBUCKET = the name of the bucket to store snapshots

import boto3
import json
import time
import sys
import os
import string

class SSWeaverController:
    def __init__(self, SimulationName):
        self.sim_name = SimulationName
        self.sim_domain = 'MyViewDomain'
        self.app_name =  'SampleApp'
        self.snapshot_bucket = {'BucketName' : os.getenv('SNAPSHOTBUCKET')}
        self.set_aws_data_path()
        self.sim_client = boto3.client('simspaceweaver')
        
    def set_aws_data_path(self):
        default_path = os.getenv('AWS_DATA_PATH')
        new_path = os.path.join(os.getcwd(), 'models')
        if (default_path == None):
            os.environ['AWS_DATA_PATH'] = new_path
        else:
            os.environ['AWS_DATA_PATH'] = default_path + ':' + new_path
        print('AWS_DATA_PATH:', os.getenv('AWS_DATA_PATH'))

    def describe_sim(self):
        return self.sim_client.describe_simulation(Simulation=self.sim_name)
        
    def start_sim(self):
        response = self.sim_client.start_simulation()
        
    def is_sim_started(self):
        response = self.describe_sim()
        return response['Status'] == 'STARTED'
    
    def start_clock(self):
        response = self.sim_client.start_clock(Simulation=self.sim_name)
    
    def is_clock_started(self):
        response = self.describe_sim()
        return response['LiveSimulationState']['Clocks'][0]['Status'] == 'STARTED'
        
    def start_app(self):
        response = self.sim_client.start_app(
            Domain=self.sim_domain, 
            Name=self.app_name,
            Simulation=self.sim_name)
    
    def is_app_started(self):
        response = self.sim_client.describe_app(
            App=self.app_name,
            Domain=self.sim_domain,
            Simulation=self.sim_name)
        return response['Status'] == 'STARTED'
        
    def create_snapshot(self):
        response = self.sim_client.create_snapshot(
            Simulation=self.sim_name,
            Destination=self.snapshot_bucket)

def main(SimulationName):
    print("SimulationName:", SimulationName)
    sim_controller=SSWeaverController(SimulationName)
    if not (sim_controller.is_sim_started()):
        print("Waiting for simulation to be STARTED...")
        return False
    print("Simulation is STARTED")
    
    try:
        print("Starting app")
        sim_controller.start_app()
    except sim_controller.sim_client.exceptions.ConflictException:
        pass # this exception means the app is already started
    
    if not (sim_controller.is_app_started()):
        print("Waiting for app to be STARTED")
        return False
    print("App is STARTED")
        
    if not (sim_controller.is_clock_started()):
        sim_controller.start_clock()        
        print("Waiting for clock to be STARTED")
        return False
    print("Clock is STARTED")
    
    print("Taking snapshot")
    sim_controller.create_snapshot()
    print("Snapshot created")
    return True

def lambda_handler(event, context):
    print("event:", event)
    snapshot_taken = main(event['simulation_name'])
    return { 
        'SnapshotTaken' : snapshot_taken
    }
if __name__=='__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("ERROR: Simulation name argument is required")
    
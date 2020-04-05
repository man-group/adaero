import { Component, OnInit, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { ApiService, RequestStatusPayload, MetadataPayload, Metadata } from '../../../services/api.service';

@Component({
  selector: 'app-request',
  templateUrl: './request.component.html',
  styleUrls: ['./request.component.scss']
})
export class RequestComponent implements OnInit {

  successMsg: string;
  errorMsg: string;
  metadata: Metadata;
  status: RequestStatusPayload | {};
  constructor(private api: ApiService) { }

  ngOnInit() {
    this.fetchStatus();
    this.api.getMetadata().subscribe(
      (result: MetadataPayload) => {
        this.metadata = result.metadata;
      },
    );
  }

  fetchStatus() {
    this.api.getRequestStatus().subscribe((payload) => {
      this.status = payload;
    });
  }

  onSubmit(form: NgForm) {
    this.successMsg = null;
    this.errorMsg = null;
    this.api.sendRequest(form.value.email).subscribe(() => {
      this.successMsg = 'Invite successfully sent!';
    }, (error) => {
      this.errorMsg = error.error ? error.error.message : error.message;
    });
  }

}

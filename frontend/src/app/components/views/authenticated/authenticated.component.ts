import { Component, OnInit } from '@angular/core';
import { ApiService, UserData, MetadataPayload, Metadata } from '../../../services/api.service';

@Component({
  selector: 'app-authenticated',
  templateUrl: './authenticated.component.html',
  styleUrls: ['./authenticated.component.scss']
})
export class AuthenticatedComponent implements OnInit {

  user: UserData;
  public metadata: Metadata;
  constructor(private api: ApiService) { }

  ngOnInit() {
    this.fetchData();
  }

  fetchData() {
    this.api.getUserData().subscribe((result) => {
      this.user = result;
    });
    this.api.getMetadata().subscribe(
      (result: MetadataPayload) => {
        this.metadata = result.metadata;
      },
    );
  }

}

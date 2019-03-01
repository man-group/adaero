import { Component, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { ApiService } from '../../../services/api.service';

@Component({
  templateUrl: './self-nominate.component.html',
  selector: 'app-self-nominate'
})
export class SelfNominateComponent implements OnInit {
    isLoaded = false;
    data = null;
    endpoint = '/self-nominate';

    constructor(private api: ApiService, private router: Router) {}

    ngOnInit() {
      this.fetchTemplate();
    }

    fetchTemplate() {
      this.api.fetchTemplate(this.endpoint).subscribe(
        (data) => {
          this.data = data;
          this.isLoaded = true;
        }
      );
    }

    onClick() {
      if (this.data.canNominate) {
        this.api.selfNominate().subscribe(
          (data) => {
            this.data = data;
            this.isLoaded = true;
          }
        );
      } else {
          this.router.navigate([this.data.buttonLink]);
      }
    }
}

import { Component, Input, OnInit } from '@angular/core';
import { Router } from '@angular/router';

import { ApiService } from '../../../services/api.service';

@Component({
  templateUrl: './enrol.component.html',
  selector: 'app-enrol'
})
export class EnrolComponent implements OnInit {
    isLoaded = false;
    data = null;
    endpoint = '/enrol';

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
      if (this.data.canEnrol) {
        this.api.enrol().subscribe(
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
